#!/usr/bin/env python3
"""
简化测试脚本，验证replace_N_region函数的逻辑
"""

import re

def replace_N_region(seq, kmer_pattern, chosen_kmer):
    """
    Replace N region in sequence based on kmer_pattern and chosen_kmer.
    """
    # 解析 kmer_pattern 来提取上游和下游序列
    pattern_match = re.match(r'^(.+?)\{N(\d+)\}(.+)$', kmer_pattern)
    if not pattern_match:
        print(f"❌ 无法解析 kmer_pattern: {kmer_pattern}")
        return seq
    
    upstream_seq = pattern_match.group(1)
    n_length = int(pattern_match.group(2))
    downstream_seq = pattern_match.group(3)
    
    print(f"解析模式:")
    print(f"  上游序列: {upstream_seq}")
    print(f"  N长度: {n_length}")
    print(f"  下游序列: {downstream_seq}")
    
    # 在序列中查找上游序列的位置
    upstream_pos = seq.find(upstream_seq)
    if upstream_pos == -1:
        print(f"❌ 在序列中找不到上游序列: {upstream_seq}")
        return seq
    
    # 在序列中查找下游序列的位置
    downstream_pos = seq.find(downstream_seq, upstream_pos + len(upstream_seq))
    if downstream_pos == -1:
        print(f"❌ 在序列中找不到下游序列: {downstream_seq}")
        return seq
    
    print(f"找到位置:")
    print(f"  上游位置: {upstream_pos}")
    print(f"  下游位置: {downstream_pos}")
    
    # 验证 chosen_kmer 的格式
    if not chosen_kmer.startswith(upstream_seq):
        print(f"❌ chosen_kmer 不以上游序列开头")
        return seq
    
    if not chosen_kmer.endswith(downstream_seq):
        print(f"❌ chosen_kmer 不以下游序列结尾")
        return seq
    
    # 提取 chosen_kmer 中需要填充到 N 区域的部分
    fill_start = len(upstream_seq)
    fill_end = len(chosen_kmer) - len(downstream_seq)
    fill_sequence = chosen_kmer[fill_start:fill_end]
    
    print(f"提取的填充序列: {fill_sequence}")
    
    # 构建新序列：上游序列 + 填充序列 + 下游序列
    new_seq = (seq[:upstream_pos] + 
               upstream_seq + 
               fill_sequence + 
               downstream_seq + 
               seq[downstream_pos + len(downstream_seq):])
    
    print(f"替换完成")
    return new_seq

def get_consecutive_N_regions(seq):
    """
    Identify consecutive N regions in a sequence and return them as dictionaries.
    """
    n_regions = []
    i = 0
    while i < len(seq):
        if seq[i] == 'N':
            n_start = i
            while i < len(seq) and seq[i] == 'N':
                i += 1
            n_end = i - 1
            n_regions.append({'nstart': n_start, 'nend': n_end})
        else:
            i += 1
    return n_regions

def test_sequential_filling():
    """
    测试顺序填充逻辑
    """
    print("=== 测试顺序填充逻辑 ===")
    
    # 模拟有多个N区域的序列
    seq = "ATCGATCGATCGATCGNNNNNNNNNNNNATCGATCGATCGATCGNNNNNNNNNNNNATCGATCGATCGATCG"
    print(f"原始序列: {seq}")
    print(f"序列长度: {len(seq)}")
    
    iteration = 0
    max_iterations = 10
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- 第 {iteration} 轮处理 ---")
        
        # 重新计算N区域
        n_regions = get_consecutive_N_regions(seq)
        n_regions_count = len(n_regions)
        print(f"N区域数量: {n_regions_count}")
        print(f"N区域: {n_regions}")
        
        if n_regions_count == 0:
            print("✅ 所有N区域已填充完成")
            break
        
        # 处理第一个N区域
        n_region = n_regions[0]
        n_start = n_region['nstart']
        n_end = n_region['nend']
        print(f"处理N区域: 位置 {n_start}-{n_end}")
        
        # 模拟填充（用A替换N）
        replacement = 'A' * (n_end - n_start + 1)
        seq = seq[:n_start] + replacement + seq[n_end+1:]
        print(f"填充后的序列: {seq}")
    
    print(f"\n最终序列: {seq}")
    print(f"处理轮数: {iteration}")

if __name__ == "__main__":
    test_sequential_filling()
