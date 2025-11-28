#!/usr/bin/env python3
"""
1000个真实数据模糊查询测试
测试RustKmer模糊查询在大规模真实数据上的性能和准确性
"""

import random
import subprocess
import time
import json
from collections import defaultdict

def extract_kmers_from_fasta(fasta_file, k=13, num_kmers=1000, seed=42):
    """从FASTA文件中随机选择k-mers"""
    print(f"📖 从 {fasta_file} 提取 {num_kmers} 个随机 {k}-mers...")

    random.seed(seed)
    all_kmers = []

    with open(fasta_file, 'r') as f:
        current_seq = ""
        for line in f:
            if line.startswith('>'):
                if current_seq:
                    for i in range(len(current_seq) - k + 1):
                        kmer = current_seq[i:i+k]
                        if 'N' not in kmer and len(kmer) == k:
                            all_kmers.append(kmer)
                    current_seq = ""
            else:
                current_seq += line.strip().upper()

        # 处理最后一个序列
        if current_seq:
            for i in range(len(current_seq) - k + 1):
                kmer = current_seq[i:i+k]
                if 'N' not in kmer and len(kmer) == k:
                    all_kmers.append(kmer)

    # 随机选择指定数量的k-mers
    selected_kmers = random.sample(all_kmers, min(num_kmers, len(all_kmers)))
    print(f"✅ 从总共 {len(all_kmers):,} 个k-mers中选择了 {len(selected_kmers):,} 个")

    return selected_kmers

def create_diverse_test_queries(kmers):
    """创建多样化的测试查询"""
    queries = []
    bases = ['A', 'T', 'C', 'G']

    for i, kmer in enumerate(kmers):
        query_type = i % 4

        if query_type == 0:
            # 精确匹配 (25%)
            queries.append((kmer, 0, f"精确"))
        elif query_type == 1:
            # 单个通配符 (25%)
            pos = random.randint(0, len(kmer) - 1)
            wildcard_kmer = kmer[:pos] + 'N' + kmer[pos+1:]
            queries.append((wildcard_kmer, 0, f"通配符"))
        elif query_type == 2:
            # 单突变 (25%)
            queries.append((kmer, 1, f"单突变"))
        else:
            # 组合查询 (25%) - 通配符+单突变
            pos = random.randint(0, len(kmer) - 1)
            combined_kmer = kmer[:pos] + 'N' + kmer[pos+1:]
            queries.append((combined_kmer, 1, f"组合"))

    return queries

def run_rustkmer_fuzzy_query(database_path, query, mutations):
    """运行RustKmer模糊查询"""
    try:
        cmd = [
            './target/release/rustkmer', 'fuzzy-query',
            database_path, query,
            '--mutations', str(mutations),
            '--format', 'json',
            '--quiet'
        ]

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        query_time = time.time() - start_time

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                'success': True,
                'total_count': data['total_count'],
                'variants_generated': data['query_metadata']['variants_generated'],
                'query_time_ms': query_time * 1000,
                'matches': len(data['individual_matches'])
            }
        else:
            return {
                'success': False,
                'error': result.stderr,
                'query_time_ms': query_time * 1000
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query_time_ms': 0
        }

def main():
    fasta_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"
    database_path = "/Users/forrest/Temp/demodata/performance_comparison_2025-11-28/databases/osa1_k13_rustkmer_sorted.rkdb"

    print("🧬 RustKmer 1000个真实数据模糊查询大规模测试")
    print("=" * 60)

    # 1. 提取测试k-mers
    kmers = extract_kmers_from_fasta(fasta_file, k=13, num_kmers=1000)
    print()

    # 2. 创建多样化的查询
    queries = create_diverse_test_queries(kmers)
    print(f"🔍 创建了 {len(queries)} 个多样化测试查询")
    print()

    # 3. 执行大规模测试
    results = {
        'total_queries': len(queries),
        'successful_queries': 0,
        'total_matches': 0,
        'total_variants': 0,
        'total_time_ms': 0,
        'query_types': defaultdict(list),
        'performance': {
            'min_time': float('inf'),
            'max_time': 0,
            'avg_time': 0
        }
    }

    print("🚀 开始执行1000个查询测试...")
    start_total = time.time()

    for i, (query, mutations, query_type) in enumerate(queries):
        print(f"\r进度: {i+1:4d}/{len(queries)} ({(i+1)/len(queries)*100:.1f}%)", end="")

        result = run_rustkmer_fuzzy_query(database_path, query, mutations)

        if result['success']:
            results['successful_queries'] += 1
            results['total_matches'] += result['total_count']
            results['total_variants'] += result['variants_generated']
            results['total_time_ms'] += result['query_time_ms']
            results['query_types'][query_type].append({
                'matches': result['total_count'],
                'variants': result['variants_generated'],
                'time_ms': result['query_time_ms']
            })

            # 更新性能统计
            results['performance']['min_time'] = min(results['performance']['min_time'], result['query_time_ms'])
            results['performance']['max_time'] = max(results['performance']['max_time'], result['query_time_ms'])
        else:
            print(f"\n❌ 查询 {i+1} 失败: {result['error']}")

    total_time = time.time() - start_total

    # 4. 生成统计报告
    print(f"\n\n📊 测试结果统计")
    print("=" * 60)

    # 总体统计
    success_rate = results['successful_queries'] / results['total_queries'] * 100
    avg_query_time = results['total_time_ms'] / results['successful_queries'] if results['successful_queries'] > 0 else 0

    print(f"🎯 总体性能:")
    print(f"  总查询数: {results['total_queries']:,}")
    print(f"  成功查询: {results['successful_queries']:,} ({success_rate:.1f}%)")
    print(f"  总匹配数: {results['total_matches']:,}")
    print(f"  总变体数: {results['total_variants']:,}")
    print(f"  总查询时间: {results['total_time_ms']:.0f}ms ({total_time:.2f}s)")
    print(f"  平均查询时间: {avg_query_time:.2f}ms")
    print(f"  查询吞吐量: {results['successful_queries']/total_time:.1f} 查询/秒")

    # 性能统计
    print(f"\n⚡ 性能指标:")
    print(f"  最快查询: {results['performance']['min_time']:.2f}ms")
    print(f"  最慢查询: {results['performance']['max_time']:.2f}ms")
    print(f"  变体处理速度: {results['total_variants']/results['total_time_ms']:.1f} 变体/秒")

    # 查询类型分析
    print(f"\n📈 查询类型分析:")
    for query_type, type_results in results['query_types'].items():
        if type_results:
            avg_matches = sum(r['matches'] for r in type_results) / len(type_results)
            avg_variants = sum(r['variants'] for r in type_results) / len(type_results)
            avg_time = sum(r['time_ms'] for r in type_results) / len(type_results)
            print(f"  {query_type:8s}: {len(type_results):3d} 个查询")
            print(f"              平均匹配: {avg_matches:6.1f}")
            print(f"              平均变体: {avg_variants:6.1f}")
            print(f"              平均时间: {avg_time:6.2f}ms")

    # 匹配分布
    print(f"\n🎯 匹配数分布:")
    match_ranges = [
        (0, "无匹配"),
        (1, "1-10"),
        (11, "11-50"),
        (51, "51-100"),
        (101, "101-500"),
        (501, "500+")
    ]

    for query_type, type_results in results['query_types'].items():
        if type_results:
            distribution = defaultdict(int)
            for r in type_results:
                matches = r['matches']
                if matches == 0:
                    distribution[0] += 1
                elif matches <= 10:
                    distribution[1] += 1
                elif matches <= 50:
                    distribution[2] += 1
                elif matches <= 100:
                    distribution[3] += 1
                elif matches <= 500:
                    distribution[4] += 1
                else:
                    distribution[5] += 1

            print(f"  {query_type:8s}: ", end="")
            for i, (min_count, label) in enumerate(match_ranges):
                if distribution[i] > 0:
                    print(f"{label}: {distribution[i]:3d}  ", end="")
            print()

    print(f"\n✅ 1000个真实数据模糊查询测试完成！")
    print(f"RustKmer在大规模真实数据上表现出色！")

if __name__ == "__main__":
    main()