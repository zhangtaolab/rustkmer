#!/usr/bin/env python3
"""
测试修复后的替换逻辑
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
    
    # 计算替换位置：上游序列结束位置+1 到 下游序列开始位置-1
    replace_start = upstream_pos + len(upstream_seq)
    replace_end = downstream_pos
    
    print(f"替换范围: {replace_start} 到 {replace_end}")
    print(f"原始N区域: {seq[replace_start:replace_end]}")
    
    # 构建新序列：序列前缀 + 填充序列 + 序列后缀
    new_seq = (seq[:replace_start] + 
               fill_sequence + 
               seq[replace_end:])
    
    print(f"替换完成")
    return new_seq

def test_replacement():
    # 测试数据
    seq = 'TACTTGATTAGTATAAGTTGTGTAGCTAAATCTTCTAGGATTTGCATTAATGCTAGTATAATGTCTAACTACTGGGTCTATAGTCTGCTTAGGCTAAGTCAAGAGCTATGGGTTNNNNNNNNNNNNGAGAATTAGTTGCTCTACTTCAGATTGCAAAGTTTGTAGAGTAATAAGGGGTAATTTAAGCATGGGGCTTAGGTTACAACTTAT'
    kmer_pattern = 'TGGGTT{N45}GAGAAT'
    chosen_kmer = 'TGGGTTCATCTTGATCTACTTCCTTTGCACCTTTTCCAAGCTTGGGACATTGAGAAT'
    
    print("测试替换逻辑:")
    print(f"原始序列长度: {len(seq)}")
    print(f"原始序列: {seq[:200]}...")
    
    result = replace_N_region(seq, kmer_pattern, chosen_kmer)
    
    print(f"\n结果序列长度: {len(result)}")
    print(f"结果序列: {result[:200]}...")
    
    # 验证替换是否正确
    # 检查是否包含预期的填充序列
    if 'TGGGTTCATCTTGATCTACTTCCTTTGCACCTTTTCCAAGCTTGGGACATTGAGAAT' in result:
        print("✅ 替换成功，chosen_kmer在结果中")
    else:
        print("❌ 替换失败")

if __name__ == "__main__":
    test_replacement()
