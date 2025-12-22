#!/usr/bin/env python3
"""
调试替换逻辑的问题
"""

def debug_replacement():
    """调试替换逻辑"""
    print("=== 调试替换逻辑问题 ===")
    
    # 用户遇到的具体情况
    seq = "GCGTGCGCGCGGGCGAAGGGCGGCTACGGCGTTGGCGGCAAAGAAAGTGGTGATGGACTGTAGCTGCCATGGGCGGCAGCGACAATCATGGTGGTAGGTCCACCCTGACCTCCGAGCGTGAAGCGGCGCGGGCGGCGGGCACGGCGACGCCGAGGCCGGTGATCATGGTGGAGAAGACGACGCCCAGGAGCGCCGCCCGTGGAGATCCACGAGCTGCGCGTGTCGGAGGTCGGGCAGCGCGGAGCTTACAGGGTGTAAACAGTAGTAGTAGCATTATTATGTCTTGTAAGTTGTAGAAGTCGCCGGGCTTGCCATTGATGGTGTAGGCGTCGGTACGTGCGGGCGACACANNNNNNNCGGGAACGGGGCCGGCGCG"
    
    upstream_seq = "CGACACA"
    downstream_seq = "CGGGAAC"
    upstream_marker = "CGACACAN"
    downstream_marker = "NCGGGAAC"
    
    upstream_pos = 343
    downstream_pos = 356
    downstream_seq_pos = 357
    
    print(f"序列长度: {len(seq)}")
    print(f"N区域位置: 350-356 (7个N)")
    print(f"上游序列: {upstream_seq}")
    print(f"下游序列: {downstream_seq}")
    print(f"上游标记: {upstream_marker}")
    print(f"下游标记: {downstream_marker}")
    print(f"上游标记位置: {upstream_pos}")
    print(f"下游标记位置: {downstream_pos}")
    print(f"下游序列位置: {downstream_seq_pos}")
    
    # 检查是否是共享N的情况
    shared_n = (downstream_seq_pos == upstream_pos + len(upstream_seq) + 1)
    print(f"共享N情况: {shared_n}")
    
    # 计算替换位置
    if shared_n:
        replace_start = upstream_pos + len(upstream_seq)  # 上游序列结束后
        replace_end = downstream_seq_pos  # 下游序列开始前
    else:
        replace_start = upstream_pos + len(upstream_marker)  # 上游标记结束后
        replace_end = downstream_pos + len(downstream_marker) - 1  # 下游标记开始前
    
    print(f"\n替换位置计算:")
    print(f"replace_start: {replace_start}")
    print(f"replace_end: {replace_end}")
    
    # 显示替换范围的内容
    original_range = seq[replace_start:replace_end]
    print(f"替换范围内容: '{original_range}'")
    print(f"替换范围长度: {len(original_range)}")
    
    # 检查N的位置
    n_positions = [i for i, c in enumerate(seq) if c == 'N']
    print(f"\n序列中所有N的位置: {n_positions}")
    
    # 显示替换范围的上下文
    context_start = max(0, replace_start - 10)
    context_end = min(len(seq), replace_end + 10)
    context = seq[context_start:context_end]
    print(f"\n替换范围上下文: ...{context}...")
    print(f"上下文替换范围标记: {context_start}到{context_end}")
    
    # 模拟替换
    fill_sequence = "TCACCCCATTGCTCGATGGTGCCAACAATGTGAAGAAATTTAT"
    
    new_seq = (seq[:replace_start] + 
               fill_sequence + 
               seq[replace_end:])
    
    print(f"\n替换后的序列:")
    print(f"新序列长度: {len(new_seq)}")
    
    # 检查替换后的区域
    new_context_start = max(0, replace_start - 10)
    new_context_end = min(len(new_seq), replace_start + len(fill_sequence) + 10)
    new_context = new_seq[new_context_start:new_context_end]
    print(f"替换后上下文: ...{new_context}...")
    
    # 检查是否还有N
    new_n_positions = [i for i, c in enumerate(new_seq) if c == 'N']
    print(f"替换后N的位置: {new_n_positions}")
    
    if 'N' in fill_sequence:
        print("❌ 填充序列中包含N!")
    else:
        print("✅ 填充序列中没有N")

if __name__ == "__main__":
    debug_replacement()
