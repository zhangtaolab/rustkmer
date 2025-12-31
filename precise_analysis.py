#!/usr/bin/env python3
"""
精确分析N区域边界问题
"""

def precise_analysis():
    """精确分析N区域边界"""
    print("=== 精确分析N区域边界问题 ===")
    
    # 用户遇到的具体情况
    seq = "GCGTGCGCGCGGGCGAAGGGCGGCTACGGCGTTGGCGGCAAAGAAAGTGGTGATGGACTGTAGCTGCCATGGGCGGCAGCGACAATCATGGTGGTAGGTCCACCCTGACCTCCGAGCGTGAAGCGGCGCGGGCGGCGGGCACGGCGACGCCGAGGCCGGTGATCATGGTGGAGAAGACGACGCCCAGGAGCGCCGCCCGTGGAGATCCACGAGCTGCGCGTGTCGGAGGTCGGGCAGCGCGGAGCTTACAGGGTGTAAACAGTAGTAGTAGCATTATTATGTCTTGTAAGTTGTAGAAGTCGCCGGGCTTGCCATTGATGGTGTAGGCGTCGGTACGTGCGGGCGACACANNNNNNNCGGGAACGGGGCCGGCGCG"
    
    print(f"序列总长度: {len(seq)}")
    
    # 找到所有N的位置
    n_positions = [i for i, c in enumerate(seq) if c == 'N']
    print(f"所有N的位置: {n_positions}")
    
    # 找到连续的N区域
    n_regions = []
    if n_positions:
        start = n_positions[0]
        end = n_positions[0]
        for i in range(1, len(n_positions)):
            if n_positions[i] == n_positions[i-1] + 1:  # 连续
                end = n_positions[i]
            else:  # 不连续
                n_regions.append((start, end))
                start = n_positions[i]
                end = n_positions[i]
        n_regions.append((start, end))  # 最后一个区域
    
    print(f"N区域: {n_regions}")
    
    # 分析第一个N区域
    if n_regions:
        n_start, n_end = n_regions[0]
        n_region_seq = seq[n_start:n_end+1]
        print(f"\n第一个N区域:")
        print(f"位置: {n_start}-{n_end}")
        print(f"内容: '{n_region_seq}'")
        print(f"长度: {len(n_region_seq)}")
        
        # 显示N区域的上下文
        context_start = max(0, n_start - 10)
        context_end = min(len(seq), n_end + 20)
        context = seq[context_start:context_end]
        print(f"上下文: ...{context}...")
        
        # 标记N区域在上下文中的位置
        n_start_in_context = n_start - context_start
        n_end_in_context = n_end - context_start
        print(f"N在上下文中的位置: {n_start_in_context}-{n_end_in_context}")
        
        # 显示替换应该覆盖的范围
        print(f"\n替换分析:")
        print(f"应该替换的N区域: {n_start}-{n_end}")
        
        # 用户说的替换范围
        user_replace_start = 351
        user_replace_end = 363
        user_range = seq[user_replace_start:user_replace_end]
        print(f"用户报告的替换范围: {user_replace_start}-{user_replace_end}")
        print(f"用户替换范围内容: '{user_range}'")
        
        # 检查是否匹配
        if user_replace_start <= n_start and user_replace_end >= n_end:
            print("✅ 用户替换范围覆盖了整个N区域")
        else:
            print("❌ 用户替换范围没有覆盖整个N区域")
            print(f"遗漏的N位置: ", end="")
            for i in range(n_start, n_end+1):
                if i < user_replace_start or i > user_replace_end:
                    print(f"{i} ", end="")
            print()

if __name__ == "__main__":
    precise_analysis()
