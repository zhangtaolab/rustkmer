#!/usr/bin/env python3
"""
测试共享N情况的替换逻辑
"""

import re

def replace_N_region_test(seq, kmer_pattern, chosen_kmer):
    """
    测试版本的替换函数
    """
    import re
    
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
    
    # 查找标记序列：上游序列+最后一个N，下游序列+第一个N
    upstream_marker = upstream_seq + 'N'
    downstream_marker = 'N' + downstream_seq
    
    print(f"上游标记: {upstream_marker}")
    print(f"下游标记: {downstream_marker}")
    
    # 在序列中查找上游标记的位置
    upstream_pos = seq.find(upstream_marker)
    if upstream_pos == -1:
        print(f"❌ 在序列中找不到上游标记: {upstream_marker}")
        return seq
    
    print(f"找到上游标记位置: {upstream_pos}")
    
    # 在序列中查找下游序列的位置（从上游标记结束后开始）
    # 但是要处理下游标记的第一个N就是上游标记最后一个N的情况（当N长度为1时）
    downstream_seq_pos = seq.find(downstream_seq, upstream_pos + len(upstream_marker) - 1)
    if downstream_seq_pos == -1:
        print(f"❌ 在序列中找不到下游序列: {downstream_seq}")
        return seq
    
    print(f"找到下游序列位置: {downstream_seq_pos}")
    
    # 检查是否是共享N的情况（即下游标记的第一个N就是上游标记的最后一个N）
    # 在序列 "ACTTGAANACATAGA" 中：
    # 上游序列 "ACTTGAA" 在位置 44-50，N 在位置 51，下游序列 "ACATAGA" 在位置 52
    # 所以共享N的条件是：downstream_seq_pos == upstream_pos + len(upstream_seq) + 1
    shared_n = (downstream_seq_pos == upstream_pos + len(upstream_seq) + 1)
    if shared_n:
        print("检测到共享N的情况：下游标记的第一个N就是上游标记的最后一个N")
        downstream_pos = downstream_seq_pos - 1  # 下游标记的开始位置是N的位置
    else:
        downstream_pos = seq.find(downstream_marker, upstream_pos + len(upstream_marker))
        if downstream_pos == -1:
            print(f"❌ 在序列中找不到下游标记: {downstream_marker}")
            return seq
    
    print(f"找到标记位置:")
    print(f"  上游标记位置: {upstream_pos}")
    print(f"  下游标记位置: {downstream_pos}")
    
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
    
    # 计算替换位置
    if shared_n:
        # 共享N的情况：N区域是从上游序列结束后到下游序列开始前
        replace_start = upstream_pos + len(upstream_seq)  # 上游序列结束后
        replace_end = downstream_seq_pos  # 下游序列开始前
    else:
        # 正常情况：上游标记结束位置+1 到 下游标记开始位置-1
        replace_start = upstream_pos + len(upstream_marker)  # 上游标记结束后
        replace_end = downstream_pos + len(downstream_marker) - 1  # 下游标记开始前
    
    print(f"替换范围: {replace_start} 到 {replace_end}")
    print(f"原始N区域: {seq[replace_start:replace_end]}")
    
    # 构建新序列：序列前缀 + 填充序列 + 序列后缀
    new_seq = (seq[:replace_start] + 
               fill_sequence + 
               seq[replace_end:])
    
    print(f"替换完成")
    return new_seq


def test_shared_n_case():
    print("=== 测试共享N情况的替换逻辑 ===")
    
    # 模拟用户遇到的情况
    seq = "CAGCCCGCCTTTTATACTGTAGGTTACATGTGTCTCCAAGTAAGACTTGAANACATAGAACCCAATACGATATCCGG"
    kmer_pattern = "ACTTGAA{N43}ACATAGA"
    chosen_kmer = "ACTTGAAGTACGATCGATCGTAGCTAGCTAGCTAGCTAGCTACATAGA"
    
    print(f"原始序列: {seq}")
    print(f"kmer模式: {kmer_pattern}")
    print(f"选择的kmer: {chosen_kmer}")
    
    # 提取相关片段
    upstream_seq = "ACTTGAA"
    downstream_seq = "ACATAGA"
    print(f"\\n相关序列片段:")
    pos = seq.find(upstream_seq)
    if pos != -1:
        fragment = seq[pos:pos+20]
        print(f"序列片段: {fragment}")
    
    result = replace_N_region_test(seq, kmer_pattern, chosen_kmer)
    
    print(f"\\n替换结果: {result}")
    
    # 验证结果
    if result != seq:
        print("✅ 替换成功执行")
        # 检查是否还有N
        if 'N' not in result[result.find(upstream_seq):result.find(downstream_seq)+len(downstream_seq)]:
            print("✅ N区域已正确替换")
        else:
            print("❌ 仍有N区域未替换")
    else:
        print("❌ 替换未执行")


if __name__ == "__main__":
    test_shared_n_case()
