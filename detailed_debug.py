#!/usr/bin/env python3
"""
详细调试替换逻辑
"""

def detailed_debug():
    """详细调试替换逻辑"""
    print("=== 详细调试替换逻辑 ===")
    
    # 用户遇到的具体情况
    seq = "GCGTGCGCGCGGGCGAAGGGCGGCTACGGCGTTGGCGGCAAAGAAAGTGGTGATGGACTGTAGCTGCCATGGGCGGCAGCGACAATCATGGTGGTAGGTCCACCCTGACCTCCGAGCGTGAAGCGGCGCGGGCGGCGGGCACGGCGACGCCGAGGCCGGTGATCATGGTGGAGAAGACGACGCCCAGGAGCGCCGCCCGTGGAGATCCACGAGCTGCGCGTGTCGGAGGTCGGGCAGCGCGGAGCTTACAGGGTGTAAACAGTAGTAGTAGCATTATTATGTCTTGTAAGTTGTAGAAGTCGCCGGGCTTGCCATTGATGGTGTAGGCGTCGGTACGTGCGGGCGACACANNNNNNNCGGGAACGGGGCCGGCGCG"
    
    print(f"序列总长度: {len(seq)}")
    
    # 显示N区域
    n_region = seq[350:357]  # 位置350-356
    print(f"N区域 (350-356): '{n_region}'")
    print(f"N区域长度: {len(n_region)}")
    
    # 显示上下游序列
    upstream_seq = "CGACACA"
    downstream_seq = "CGGGAAC"
    
    print(f"上游序列: '{upstream_seq}'")
    print(f"下游序列: '{downstream_seq}'")
    
    # 查找标记位置
    upstream_marker = "CGACACAN"
    downstream_marker = "NCGGGAAC"
    
    upstream_pos = 343
    downstream_pos = 356
    downstream_seq_pos = 357
    
    print(f"\n标记位置:")
    print(f"上游标记 '{upstream_marker}' 位置: {upstream_pos}")
    print(f"下游标记 '{downstream_marker}' 位置: {downstream_pos}")
    print(f"下游序列 '{downstream_seq}' 位置: {downstream_seq_pos}")
    
    # 检查标记内容
    actual_upstream_marker = seq[upstream_pos:upstream_pos + len(upstream_marker)]
    actual_downstream_marker = seq[downstream_pos:downstream_pos + len(downstream_marker)]
    actual_downstream_seq = seq[downstream_seq_pos:downstream_seq_pos + len(downstream_seq)]
    
    print(f"\n实际序列内容:")
    print(f"上游标记实际内容: '{actual_upstream_marker}'")
    print(f"下游标记实际内容: '{actual_downstream_marker}'")
    print(f"下游序列实际内容: '{actual_downstream_seq}'")
    
    # 检查共享N条件
    shared_n_condition = downstream_seq_pos == upstream_pos + len(upstream_seq) + 1
    print(f"\n共享N条件检查:")
    print(f"downstream_seq_pos (357) == upstream_pos + len(upstream_seq) + 1 ({upstream_pos} + {len(upstream_seq)} + 1 = {upstream_pos + len(upstream_seq) + 1})")
    print(f"共享N判断: {shared_n_condition}")
    
    # 计算替换位置
    if shared_n_condition:
        replace_start = upstream_pos + len(upstream_seq)  # 上游序列结束后
        replace_end = downstream_seq_pos  # 下游序列开始前
        print(f"\n共享N情况:")
        print(f"replace_start = {upstream_pos} + {len(upstream_seq)} = {replace_start}")
        print(f"replace_end = {downstream_seq_pos} = {replace_end}")
    else:
        replace_start = upstream_pos + len(upstream_marker)  # 上游标记结束后
        replace_end = downstream_pos + len(downstream_marker) - 1  # 下游标记开始前
        print(f"\n非共享N情况:")
        print(f"replace_start = {upstream_pos} + {len(upstream_marker)} = {replace_start}")
        print(f"replace_end = {downstream_pos} + {len(downstream_marker)} - 1 = {replace_end}")
    
    # 显示替换范围
    original_range = seq[replace_start:replace_end]
    print(f"\n替换范围: {replace_start} 到 {replace_end}")
    print(f"替换范围内容: '{original_range}'")
    print(f"替换范围长度: {len(original_range)}")
    
    # 检查替换后的结果
    fill_sequence = "TCACCCCATTGCTCGATGGTGCCAACAATGTGAAGAAATTTAT"
    new_seq = seq[:replace_start] + fill_sequence + seq[replace_end:]
    
    # 检查替换后的区域
    new_range = new_seq[replace_start:replace_start + len(fill_sequence)]
    print(f"\n替换后的区域: '{new_range}'")
    
    # 检查是否还有N
    n_count_in_range = new_range.count('N')
    print(f"替换后区域中N的数量: {n_count_in_range}")
    
    if n_count_in_range == 0:
        print("✅ 替换后没有N")
    else:
        print("❌ 替换后仍有N")

if __name__ == "__main__":
    detailed_debug()
