#!/usr/bin/env python3
"""
测试修复后的replace_N_region函数
"""

def test_new_replace_function():
    """测试新的replace_N_region函数"""
    print("=== 测试修复后的replace_N_region函数 ===")
    
    # 模拟修复后的函数
    def replace_N_region_fixed(seq, kmer_pattern, chosen_kmer, n_start, n_end):
        """修复后的replace_N_region函数"""
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
        print(f"N区域边界: {n_start}-{n_end}")
        
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
        
        # 直接使用N区域的边界作为替换范围
        replace_start = n_start
        replace_end = n_end + 1  # Python切片是左闭右开的，所以+1
        
        print(f"替换范围: {replace_start} 到 {replace_end}")
        original_n_region = seq[replace_start:replace_end]
        print(f"原始N区域: '{original_n_region}'")
        
        # 验证替换范围是否包含N
        n_count = original_n_region.count('N')
        print(f"替换范围中N的数量: {n_count}")
        if n_count == 0:
            print("⚠️ 警告：替换范围中没有N！")
            return seq
        
        # 构建新序列：序列前缀 + 填充序列 + 序列后缀
        new_seq = (seq[:replace_start] + 
                   fill_sequence + 
                   seq[replace_end:])
        
        print(f"替换完成")
        return new_seq
    
    # 测试数据
    seq = "GCGTGCGCGCGGGCGAAGGGCGGCTACGGCGTTGGCGGCAAAGAAAGTGGTGATGGACTGTAGCTGCCATGGGCGGCAGCGACAATCATGGTGGTAGGTCCACCCTGACCTCCGAGCGTGAAGCGGCGCGGGCGGCGGGCACGGCGACGCCGAGGCCGGTGATCATGGTGGAGAAGACGACGCCCAGGAGCGCCGCCCGTGGAGATCCACGAGCTGCGCGTGTCGGAGGTCGGGCAGCGCGGAGCTTACAGGGTGTAAACAGTAGTAGTAGCATTATTATGTCTTGTAAGTTGTAGAAGTCGCCGGGCTTGCCATTGATGGTGTAGGCGTCGGTACGTGCGGGCGACACANNNNNNNCGGGAACGGGGCCGGCGCG"
    kmer_pattern = "CGACACA{N43}CGGGAAC"
    chosen_kmer = "CGACACATCACCCCATTGCTCGATGGTGCCAACAATGTGAAGAAATTTATCGGGAAC"
    n_start = 350
    n_end = 356
    
    print(f"原始序列长度: {len(seq)}")
    print(f"测试N区域: {n_start}-{n_end}")
    
    # 执行替换
    result = replace_N_region_fixed(seq, kmer_pattern, chosen_kmer, n_start, n_end)
    
    print(f"\n=== 替换结果验证 ===")
    print(f"结果序列长度: {len(result)}")
    
    # 检查替换后的N区域
    new_n_region = result[n_start:n_end+1]
    print(f"替换后N区域: '{new_n_region}'")
    print(f"替换后N区域中N的数量: {new_n_region.count('N')}")
    
    # 显示替换后的上下文
    context_start = max(0, n_start - 10)
    context_end = min(len(result), n_end + 20)
    context = result[context_start:context_end]
    print(f"替换后上下文: ...{context}...")
    
    if new_n_region.count('N') == 0:
        print("✅ 替换成功：N区域完全替换，没有残留N")
    else:
        print("❌ 替换失败：仍有N残留")

if __name__ == "__main__":
    test_new_replace_function()
