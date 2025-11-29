#!/usr/bin/env python3
"""
真实数据模糊查询测试脚本
从OSA1基因组中随机选择1000个k-mers，用rustkmer和jellyfish进行对比测试
"""

import random
import subprocess
import sys
import time
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
                    # 提取当前序列的所有k-mers
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
    print(f"✅ 从总共 {len(all_kmers)} 个k-mers中选择了 {len(selected_kmers)} 个")

    return selected_kmers

def create_fuzzy_queries(kmers, mutation_rate=0.1, wildcard_rate=0.1):
    """创建模糊查询：部分添加突变，部分添加通配符"""
    fuzzy_queries = []
    bases = ['A', 'T', 'C', 'G']

    for i, kmer in enumerate(kmers):
        if i < len(kmers) // 3:
            # 精确匹配
            fuzzy_queries.append((kmer, 0, f"精确匹配-{i}"))
        elif i < 2 * len(kmers) // 3:
            # 单突变
            if random.random() < mutation_rate:
                pos = random.randint(0, len(kmer) - 1)
                original_base = kmer[pos]
                new_base = random.choice([b for b in bases if b != original_base])
                mutated_kmer = kmer[:pos] + new_base + kmer[pos+1:]
                fuzzy_queries.append((mutated_kmer, 1, f"单突变-{i}"))
            else:
                fuzzy_queries.append((kmer, 1, f"突变容忍-{i}"))
        else:
            # 通配符
            pos = random.randint(0, len(kmer) - 1)
            wildcard_kmer = kmer[:pos] + 'N' + kmer[pos+1:]
            fuzzy_queries.append((wildcard_kmer, 0, f"通配符-{i}"))

    return fuzzy_queries

def run_rustkmer_fuzzy_query(database_path, query, mutations):
    """运行rustkmer模糊查询"""
    try:
        cmd = [
            './target/release/rustkmer', 'fuzzy-query',
            database_path, query,
            '--mutations', str(mutations),
            '--format', 'json',
            '--quiet'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            return data['total_count'], len(data['individual_matches'])
        else:
            return None, None
    except Exception as e:
        print(f"RustKmer查询错误: {e}")
        return None, None

def run_jellyfish_query(database_path, exact_query):
    """运行jellyfish查询（仅支持精确匹配）"""
    try:
        cmd = ['jellyfish', 'query', database_path, exact_query]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line and not line.startswith('>'):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1])
            return 0
        else:
            return None
    except Exception as e:
        print(f"Jellyfish查询错误: {e}")
        return None

def main():
    fasta_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"
    rustkmer_db = "/Users/forrest/Temp/demodata/performance_comparison_2025-11-28/databases/osa1_k13_rustkmer_sorted.rkdb"
    jellyfish_db = "/Users/forrest/Temp/demodata/performance_comparison_2025-11-28/databases/osa1_k13_jellyfish.jf"

    print("🧬 RustKmer vs Jellyfish 真实数据模糊查询对比测试")
    print("=" * 60)

    # 1. 提取测试k-mers
    kmers = extract_kmers_from_fasta(fasta_file, k=13, num_kmers=1000)
    print()

    # 2. 创建模糊查询
    fuzzy_queries = create_fuzzy_queries(kmers)
    print(f"🔍 创建了 {len(fuzzy_queries)} 个模糊查询")
    print()

    # 3. 运行对比测试
    results = {
        'exact_matches': 0,
        'rustkmer_success': 0,
        'jellyfish_success': 0,
        'rustkmer_total_matches': 0,
        'rustkmer_time': 0,
        'jellyfish_time': 0,
        'query_types': defaultdict(int)
    }

    print("🚀 开始执行查询测试...")
    for i, (query, mutations, query_type) in enumerate(fuzzy_queries):
        print(f"\r进度: {i+1}/{len(fuzzy_queries)} ({(i+1)/len(fuzzy_queries)*100:.1f}%)", end="")

        # RustKmer查询
        start_time = time.time()
        rustkmer_count, rustkmer_variants = run_rustkmer_fuzzy_query(rustkmer_db, query, mutations)
        rustkmer_time = time.time() - start_time

        # Jellyfish查询（仅对精确匹配的查询）
        jellyfish_count = None
        if mutations == 0:
            # 对于通配符查询，选择第一个可能的变体
            if 'N' in query:
                # 简单地将第一个N替换为A进行对比
                exact_query = query.replace('N', 'A', 1)
            else:
                exact_query = query

            start_time = time.time()
            jellyfish_count = run_jellyfish_query(jellyfish_db, exact_query)
            jellyfish_time = time.time() - start_time

        # 统计结果
        if rustkmer_count is not None:
            results['rustkmer_success'] += 1
            results['rustkmer_total_matches'] += rustkmer_count
            results['rustkmer_time'] += rustkmer_time

        if jellyfish_count is not None:
            results['jellyfish_success'] += 1
            results['jellyfish_time'] += jellyfish_time

            # 对于精确匹配，比较结果
            if mutations == 0 and 'N' not in query:
                if rustkmer_count == jellyfish_count:
                    results['exact_matches'] += 1

        results['query_types'][query_type.split('-')[0]] += 1

    print(f"\n\n📊 测试结果统计")
    print("=" * 40)

    total_queries = len(fuzzy_queries)
    print(f"总查询数: {total_queries}")
    print(f"RustKmer成功: {results['rustkmer_success']}/{total_queries} ({results['rustkmer_success']/total_queries*100:.1f}%)")
    print(f"Jellyfish成功: {results['jellyfish_success']}/{total_queries} ({results['jellyfish_success']/total_queries*100:.1f}%)")

    if results['exact_matches'] > 0:
        exact_total = sum(1 for _, muts, _ in fuzzy_queries if muts == 0 and 'N' not in _)
        print(f"精确匹配一致: {results['exact_matches']}/{exact_total} ({results['exact_matches']/exact_total*100:.1f}%)")

    print(f"\n⏱️  性能对比:")
    if results['rustkmer_success'] > 0:
        avg_rustkmer_time = results['rustkmer_time'] / results['rustkmer_success'] * 1000
        print(f"RustKmer平均时间: {avg_rustkmer_time:.2f}ms")

    if results['jellyfish_success'] > 0:
        avg_jellyfish_time = results['jellyfish_time'] / results['jellyfish_success'] * 1000
        print(f"Jellyfish平均时间: {avg_jellyfish_time:.2f}ms")

    print(f"\n📈 查询类型分布:")
    for query_type, count in results['query_types'].items():
        print(f"  {query_type}: {count}")

    print(f"\n🎯 总匹配统计:")
    print(f"RustKmer总匹配数: {results['rustkmer_total_matches']:,}")

    print(f"\n✅ 测试完成!")

if __name__ == "__main__":
    main()