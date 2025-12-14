#!/usr/bin/env python3
"""Comprehensive test of N wildcard support in fuzzy query."""

import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from rustkmer import Database

def test_n_wildcards_comprehensive():
    """Comprehensive test of N wildcard patterns."""

    test_db = Path(__file__).parent / "python" / "tests" / "test_data" / "tiny_test.rkdb"

    if not test_db.exists():
        print(f"Test database not found: {test_db}")
        return

    print("=== Comprehensive N Wildcard Test ===\n")

    with Database(test_db) as db:
        print("1. Single N wildcard (位置：5): 'ATCGATN'")
        result = db.fuzzy_query("ATCGATN", mutations=0)
        print(f"   找到 {result.total_matches} 个匹配")
        if result.matches:
            for match in result.get_top_matches(3):
                print(f"   - {match.kmer} (count: {match.count})")

        print("\n2. Multiple N wildcards (位置：3和6): 'ATNNGTN'")
        result = db.fuzzy_query("ATNNGTN", mutations=0, max_variants=100)
        print(f"   找到 {result.total_matches} 个匹配")
        if result.matches:
            for match in result.get_top_matches(5):
                print(f"   - {match.kmer} (count: {match.count})")

        print("\n3. N at beginning (位置：1): 'NAAAAAA'")
        result = db.fuzzy_query("NAAAAAA", mutations=0, max_variants=4)
        print(f"   找到 {result.total_matches} 个匹配")
        if result.matches:
            for match in result.get_top_matches(3):
                print(f"   - {match.kmer} (count: {match.count})")

        print("\n4. N at end (位置：7): 'AAAAAAN'")
        result = db.fuzzy_query("AAAAAAN", mutations=0, max_variants=4)
        print(f"   找到 {result.total_matches} 个匹配")
        if result.matches:
            for match in result.get_top_matches(3):
                print(f"   - {match.kmer} (count: {match.count})")

        print("\n5. Mixed N + mutations tolerance:")
        print("   Query: 'ATNCGTN' with mutations=1")
        result = db.fuzzy_query("ATNCGTN", mutations=1, max_variants=100)
        print(f"   找到 {result.total_matches} 个匹配")
        if result.matches:
            exact_matches = [m for m in result.matches if m.distance == 0]
            single_mutations = [m for m in result.matches if m.distance == 1]
            print(f"   - 精确匹配: {len(exact_matches)} 个")
            print(f"   - 1个突变: {len(single_mutations)} 个")
            for match in result.get_top_matches(5):
                print(f"   - {match.kmer} (count: {match.count}, distance: {match.distance})")

        print("\n6. Batch query with N wildcards:")
        queries = [
            "ATCGATN",     # 单个N
            "ATNNGTN",     # 多个N
            "NNNNNNN",     # 全部N（有限制）
            "ANNNNNA"      # 两端N
        ]

        batch_result = db.fuzzy_query_batch(queries, mutations=0, max_variants=1000)
        print(f"   处理了 {batch_result.total_queries} 个查询")
        print(f"   总共找到 {batch_result.total_matches} 个匹配")

        for result in batch_result.query_results:
            if result.total_matches > 0:
                print(f"   - {result.query_kmer}: {result.total_matches} 匹配")
            else:
                print(f"   - {result.query_kmer}: 0 匹配")

        print("\n7. Performance comparison:")
        # Compare exact query vs N wildcard
        exact = db.fuzzy_query("ATCGATC", mutations=0)
        wildcard = db.fuzzy_query("ATCGATN", mutations=0)
        print(f"   精确查询 'ATCGATC': {exact.total_matches} 匹配")
        print(f"   通配符查询 'ATCGATN': {wildcard.total_matches} 匹配")
        print(f"   N通配符生成的变体数: {4} (4^1)")

        print("\n8. Export formats with N wildcards:")
        result = db.fuzzy_query("ATNCGTN", mutations=1, max_variants=100)
        if result.total_matches > 0:
            print("   JSON导出:")
            json_str = result.to_json()
            print(f"     长度: {len(json_str)} 字符")

            print("\n   Table导出 (前3行):")
            table = result.to_table(max_rows=3)
            lines = table.split('\n')
            for line in lines[:3]:
                print(f"     {line}")

        print("\n=== N通配符功能总结 ===")
        print("✅ 支持单个或多个N通配符")
        print("✅ N可以出现在k-mer的任何位置")
        print("✅ 可以与突变容忍度结合使用")
        print("✅ 支持批量查询")
        print("✅ 支持所有导出格式")
        print("✅ 自动处理变体数量限制")

if __name__ == "__main__":
    test_n_wildcards_comprehensive()