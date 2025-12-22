#!/usr/bin/env python3
"""
测试修复后的共享N判断
"""

def test_shared_n_fix():
    """测试修复后的共享N判断"""
    print("=== 测试修复后的共享N判断 ===")
    
    # 用户遇到的具体情况
    seq = "GCGTGCGCGCGGGCGAAGGGCGGCTACGGCGTTGGCGGCAAAGAAAGTGGTGATGGACTGTAGCTGCCATGGGCGGCAGCGACAATCATGGTGGTAGGTCCACCCTGACCTCCGAGCGTGAAGCGGCGCGGGCGGCGGGCACGGCGACGCCGAGGCCGGTGATCATGGTGGAGAAGACGACGCCCAGGAGCGCCGCCCGTGGAGATCCACGAGCTGCGCGTGTCGGAGGTCGGGCAGCGCGGAGCTTACAGGGTGTAAACAGTAGTAGTAGCATTATTATGTCTTGTAAGTTGTAGAAGTCGCCGGGCTTGCCATTGATGGTGTAGGCGTCGGTACGTGCGGGCGACACANNNNNNNCGGGAACGGGGCCGGCGCG"
    
    upstream_seq = "CGACACA"
    downstream_seq = "CGGGAAC"
    upstream_marker = "CGACACAN"
    downstream_marker = "NCGGGAAC"
    
    upstream_pos = 343
    downstream_pos = 356
    downstream_seq_pos = 357
    
    print(f"上游标记位置: {upstream_pos}")
    print(f"下游标记位置: {downstream_pos}")
    print(f"下游序列位置: {downstream_seq_pos}")
    print(f"上游序列长度: {len(upstream_seq)}")
    print(f"上游标记长度: {len(upstream_marker)}")
    
    # 原始共享N判断
    original_shared_n = (downstream_seq_pos == upstream_pos + len(upstream_seq) + 1)
    print(f"\n原始共享N判断: {original_shared_n}")
    
    # 修复后的共享N判断
    new_shared_n = (downstream_seq_pos == upstream_pos + len(upstream_seq) + 1) or \
                   (downstream_seq_pos == upstream_pos + len(upstream_marker))
    print(f"修复后共享N判断: {new_shared_n}")
    
    # 如果是共享N情况，计算正确的替换范围
    if new_shared_n:
        replace_start = upstream_pos + len(upstream_seq)  # 上游序列结束后
        replace_end = downstream_seq_pos  # 下游序列开始前
        print(f"\n共享N情况替换范围: {replace_start}-{replace_end}")
    else:
        replace_start = upstream_pos + len(upstream_marker)  # 上游标记结束后
        replace_end = downstream_pos + len(downstream_marker) - 1  # 下游标记开始前
        print(f"\n非共享N情况替换范围: {replace_start}-{replace_end}")
    
    # 验证替换范围
    n_region = seq[350:357]  # 实际的N区域
    replace_range = seq[replace_start:replace_end]
    
    print(f"\n验证:")
    print(f"实际N区域 (350-356): '{n_region}'")
    print(f"替换范围内容: '{replace_range}'")
    
    if replace_start <= 350 and replace_end >= 357:
        print("✅ 替换范围覆盖了整个N区域")
    else:
        print("❌ 替换范围没有覆盖整个N区域")
        
    # 模拟替换
    fill_sequence = "TCACCCCATTGCTCGATGGTGCCAACAATGTGAAGAAATTTAT"
    new_seq = seq[:replace_start] + fill_sequence + seq[replace_end:]
    
    # 检查替换后的N
    new_n_positions = [i for i, c in enumerate(new_seq) if c == 'N']
    print(f"替换后N的位置: {new_n_positions}")
    
    # 检查在原始N区域范围内是否还有N
    n_region_after = new_seq[350:357]
    n_count = n_region_after.count('N')
    print(f"原始N区域替换后内容: '{n_region_after}'")
    print(f"原始N区域中N的数量: {n_count}")

if __name__ == "__main__":
    test_shared_n_fix()
