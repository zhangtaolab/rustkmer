#!/usr/bin/env python3
"""
简单真实数据测试 - 从OSA1基因组提取少量k-mers进行快速测试
"""

import subprocess
import random

def extract_few_kmers(fasta_file, k=13, num_kmers=10):
    """提取少量k-mers"""
    print(f"从 {fasta_file} 提取 {num_kmers} 个 {k}-mers...")

    random.seed(42)
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

    selected_kmers = random.sample(all_kmers, min(num_kmers, len(all_kmers)))
    print(f"选择了 {len(selected_kmers)} 个k-mers")
    return selected_kmers

def test_rustkmer_queries(database_path, kmers):
    """测试RustKmer查询"""
    print("\n🧬 测试 RustKmer 模糊查询:")
    print("-" * 40)

    for i, kmer in enumerate(kmers):
        print(f"\n{i+1}. 测试 k-mer: {kmer}")

        # 精确匹配
        cmd = ['./target/release/rustkmer', 'fuzzy-query', database_path, kmer, '--quiet']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '|' in line and not line.startswith('─'):
                    parts = line.split('│')
                    if len(parts) >= 3:
                        seq = parts[1].strip()
                        count = parts[2].strip()
                        print(f"   精确匹配: {seq} = {count}")
        else:
            print(f"   精确匹配失败: {result.stderr}")

        # 通配符查询（中间一个N）
        wildcard_kmer = kmer[:6] + 'N' + kmer[7:]
        cmd = ['./target/release/rustkmer', 'fuzzy-query', database_path, wildcard_kmer, '--quiet']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            match_count = 0
            for line in lines:
                if '|' in line and not line.startswith('─'):
                    parts = line.split('│')
                    if len(parts) >= 3:
                        match_count += int(parts[2].strip())
            print(f"   通配符查询 ({wildcard_kmer}): {match_count} 总匹配")
        else:
            print(f"   通配符查询失败: {result.stderr}")

        # 单突变查询
        cmd = ['./target/release/rustkmer', 'fuzzy-query', database_path, kmer, '--mutations', '1', '--quiet']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            match_count = 0
            for line in lines:
                if '|' in line and not line.startswith('─'):
                    parts = line.split('│')
                    if len(parts) >= 3:
                        match_count += int(parts[2].strip())
            print(f"   单突变查询: {match_count} 总匹配")
        else:
            print(f"   单突变查询失败: {result.stderr}")

def test_jellyfish_comparison(database_path, kmers):
    """与Jellyfish进行对比测试"""
    print("\n🔬 与 Jellyfish 对比测试 (仅精确匹配):")
    print("-" * 40)

    jellyfish_db = "/Users/forrest/Temp/demodata/performance_comparison_2025-11-28/databases/osa1_k13_jellyfish.jf"

    matches = 0
    total = 0

    for i, kmer in enumerate(kmers):
        # RustKmer查询
        cmd = ['./target/release/rustkmer', 'fuzzy-query', database_path, kmer, '--format', 'json', '--quiet']
        result = subprocess.run(cmd, capture_output=True, text=True)

        rustkmer_count = 0
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            rustkmer_count = data['total_count']

        # Jellyfish查询
        cmd = ['jellyfish', 'query', jellyfish_db, kmer]
        result = subprocess.run(cmd, capture_output=True, text=True)

        jellyfish_count = 0
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line and not line.startswith('>'):
                    parts = line.split()
                    if len(parts) >= 2:
                        jellyfish_count = int(parts[1])
                        break

        print(f"{i+1:2d}. {kmer}: RustKmer={rustkmer_count:6d}, Jellyfish={jellyfish_count:6d}", end="")

        if rustkmer_count == jellyfish_count:
            print(" ✅")
            matches += 1
        else:
            print(" ❌")

        total += 1

    print(f"\n📊 对比结果: {matches}/{total} 一致 ({matches/total*100:.1f}%)")

def main():
    fasta_file = "/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa"
    database_path = "/Users/forrest/Temp/demodata/performance_comparison_2025-11-28/databases/osa1_k13_rustkmer_sorted.rkdb"

    print("🧬 RustKmer 真实数据快速测试")
    print("=" * 50)

    # 提取k-mers
    kmers = extract_few_kmers(fasta_file, k=13, num_kmers=10)

    # 测试RustKmer查询
    test_rustkmer_queries(database_path, kmers)

    # 与Jellyfish对比
    test_jellyfish_comparison(database_path, kmers)

if __name__ == "__main__":
    main()