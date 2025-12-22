#!/usr/bin/env python3
"""
调试下游标记匹配问题的脚本
"""

def debug_marker_finding():
    # 用户提供的替换后序列
    seq = "CAGCCCGCCTTTTATACTGTAGGTTACATGTGTCTCCAAGTAAGACTTGAANACATAGAACCCAATACGATATCCGG"
    
    # 从用户输出中提取的信息
    upstream_seq = "ACTTGAA"
    downstream_seq = "ACATAGA"
    upstream_marker = "ACTTGAAN"
    downstream_marker = "NACATAGA"
    
    print("=== 调试下游标记匹配问题 ===")
    print(f"序列片段: ...{seq[67:87]}...")
    print(f"上游序列: {upstream_seq}")
    print(f"下游序列: {downstream_seq}")
    print(f"上游标记: {upstream_marker}")
    print(f"下游标记: {downstream_marker}")
    
    # 查找上游标记
    upstream_pos = seq.find(upstream_marker)
    print(f"\n上游标记位置: {upstream_pos}")
    if upstream_pos != -1:
        print(f"上游标记内容: {seq[upstream_pos:upstream_pos + len(upstream_marker)]}")
    
    # 从上游标记结束位置开始查找下游标记
    search_start = upstream_pos + len(upstream_marker) if upstream_pos != -1 else 0
    print(f"从位置 {search_start} 开始搜索下游标记...")
    
    downstream_pos = seq.find(downstream_marker, search_start)
    print(f"下游标记位置: {downstream_pos}")
    
    if downstream_pos != -1:
        print(f"下游标记内容: {seq[downstream_pos:downstream_pos + len(downstream_marker)]}")
    else:
        print("❌ 未找到下游标记")
        
        # 手动搜索可能的匹配
        print("\n=== 手动搜索可能的匹配 ===")
        # 在序列中搜索包含下游序列的所有位置
        search_seq = downstream_seq
        manual_pos = seq.find(search_seq)
        while manual_pos != -1:
            print(f"在位置 {manual_pos} 找到 '{search_seq}'")
            # 检查前后是否有N
            context_start = max(0, manual_pos - 1)
            context_end = min(len(seq), manual_pos + len(search_seq) + 1)
            context = seq[context_start:context_end]
            print(f"  上下文: {context}")
            
            # 检查是否是下游标记
            if manual_pos > 0 and seq[manual_pos - 1] == 'N':
                print(f"  ✅ 在位置 {manual_pos-1} 找到完整的下游标记: N{search_seq}")
            
            manual_pos = seq.find(search_seq, manual_pos + 1)
    
    # 检查整个序列中的N位置
    print(f"\n=== 序列中的N位置 ===")
    n_positions = [i for i, c in enumerate(seq) if c == 'N']
    print(f"N位置: {n_positions}")
    for pos in n_positions:
        if pos < len(seq) - len(downstream_seq):
            context = seq[pos:pos + len(downstream_seq) + 1]
            print(f"位置 {pos}: {context}")
            if context.startswith('N' + downstream_seq):
                print(f"  ✅ 这就是我们要找的下游标记！")

if __name__ == "__main__":
    debug_marker_finding()
